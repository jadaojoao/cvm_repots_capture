# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from desktop.services import IntelligentSelectorService


def _init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE financial_reports (
                CD_CVM INTEGER,
                COMPANY_NAME TEXT,
                REPORT_YEAR INTEGER,
                STATEMENT_TYPE TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE company_refresh_status (
                cd_cvm INTEGER PRIMARY KEY,
                company_name TEXT,
                source_scope TEXT,
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
        conn.commit()


def _insert_complete_package(conn: sqlite3.Connection, cd_cvm: int, name: str, year: int) -> None:
    rows = [
        (cd_cvm, name, year, "BPA"),
        (cd_cvm, name, year, "BPP"),
        (cd_cvm, name, year, "DRE"),
        (cd_cvm, name, year, "DFC"),
    ]
    conn.executemany(
        """
        INSERT INTO financial_reports (CD_CVM, COMPANY_NAME, REPORT_YEAR, STATEMENT_TYPE)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )


def _seed_active_universe_cache(project_root: Path) -> None:
    cache_path = project_root / "data" / "cache" / "active_universe_cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(),
                "rows": [
                    {"cd_cvm": 9512, "company_name": "PETROBRAS", "sit": "ATIVA"},
                    {"cd_cvm": 4170, "company_name": "VALE", "sit": "ATIVA"},
                ],
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )


def test_base_health_snapshot_requires_full_package_per_company_year(tmp_path):
    project_root = tmp_path
    db_path = project_root / "data" / "db" / "cvm_financials.db"
    _init_db(db_path)
    _seed_active_universe_cache(project_root)

    now = datetime.now().replace(microsecond=0).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        _insert_complete_package(conn, 9512, "PETROBRAS", 2024)
        # 2025 da PETROBRAS parcial (sem DFC) => nao conta como coberto.
        conn.executemany(
            """
            INSERT INTO financial_reports (CD_CVM, COMPANY_NAME, REPORT_YEAR, STATEMENT_TYPE)
            VALUES (?, ?, ?, ?)
            """,
            [
                (9512, "PETROBRAS", 2025, "BPA"),
                (9512, "PETROBRAS", 2025, "BPP"),
                (9512, "PETROBRAS", 2025, "DRE"),
            ],
        )
        _insert_complete_package(conn, 4170, "VALE", 2024)
        _insert_complete_package(conn, 4170, "VALE", 2025)
        conn.execute(
            """
            INSERT INTO company_refresh_status (
                cd_cvm, company_name, source_scope, last_attempt_at, last_success_at, last_status,
                last_error, last_start_year, last_end_year, last_rows_inserted, updated_at
            ) VALUES
            (9512, 'PETROBRAS', 'local', ?, ?, 'success', NULL, 2024, 2025, 1, ?),
            (4170, 'VALE', 'local', ?, ?, 'success', NULL, 2024, 2025, 1, ?)
            """,
            (now, now, now, now, now, now),
        )
        conn.commit()

    service = IntelligentSelectorService(project_root)
    snapshot = service.build_base_health_snapshot(2024, 2025, force_refresh=True)

    assert snapshot["global"]["total_cells"] == 4
    assert snapshot["global"]["completed_cells"] == 3
    assert snapshot["global"]["missing_cells"] == 1
    per_year = {row["year"]: row for row in snapshot["per_year"]}
    assert per_year[2024]["completed"] == 2
    assert per_year[2025]["completed"] == 1
    assert snapshot["top_lagging"][0]["company_name"] == "PETROBRAS"
    assert 2025 in snapshot["top_lagging"][0]["years_missing"]
    assert 0.0 <= float(snapshot["health_score"]) <= 100.0
    assert snapshot["health_status"] in {"critico", "atencao", "ok"}
    assert snapshot["risks_summary"]["total_companies"] == 2
    assert snapshot["risks_summary"]["high"] + snapshot["risks_summary"]["medium"] + snapshot["risks_summary"]["low"] == 2
    assert snapshot["prioritized_companies"][0]["company_name"] == "PETROBRAS"
    assert snapshot["progress_delta"]["has_previous"] is False


def test_base_health_snapshot_eta_unavailable_with_low_throughput_signal(tmp_path):
    project_root = tmp_path
    db_path = project_root / "data" / "db" / "cvm_financials.db"
    _init_db(db_path)
    _seed_active_universe_cache(project_root)

    with sqlite3.connect(str(db_path)) as conn:
        _insert_complete_package(conn, 9512, "PETROBRAS", 2024)
        # Apenas 1 sucesso recente => abaixo da confianca minima.
        now = datetime.now().replace(microsecond=0).isoformat()
        conn.execute(
            """
            INSERT INTO company_refresh_status (
                cd_cvm, company_name, source_scope, last_attempt_at, last_success_at, last_status,
                last_error, last_start_year, last_end_year, last_rows_inserted, updated_at
            ) VALUES (?, ?, 'local', ?, ?, 'success', NULL, 2024, 2024, 1, ?)
            """,
            (9512, "PETROBRAS", now, now, now),
        )
        conn.commit()

    service = IntelligentSelectorService(project_root)
    snapshot = service.build_base_health_snapshot(2024, 2025, force_refresh=True)
    assert snapshot["global"]["eta_hours"] is None


def test_base_health_snapshot_includes_progress_delta_when_previous_cache_exists(tmp_path):
    project_root = tmp_path
    db_path = project_root / "data" / "db" / "cvm_financials.db"
    _init_db(db_path)
    _seed_active_universe_cache(project_root)

    with sqlite3.connect(str(db_path)) as conn:
        _insert_complete_package(conn, 9512, "PETROBRAS", 2024)
        conn.commit()

    cache_path = project_root / "data" / "cache" / "base_health_snapshot.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(),
                "start_year": 2024,
                "end_year": 2024,
                "global": {
                    "completed_cells": 0,
                    "missing_cells": 2,
                    "pct": 0.0,
                },
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    service = IntelligentSelectorService(project_root)
    snapshot = service.build_base_health_snapshot(2024, 2024, force_refresh=True)

    delta = snapshot["progress_delta"]
    assert delta["has_previous"] is True
    assert delta["delta_completed_cells"] == 1
    assert delta["delta_missing_cells"] == -1
    assert float(delta["delta_pct"]) > 0
    assert delta["trend"] == "melhora"
