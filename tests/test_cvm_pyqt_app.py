# -*- coding: utf-8 -*-
import json
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from desktop.services import IntelligentSelectorService, _minmax_normalize, _safe_name
from desktop.workers import UpdateWorker


def _create_db(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE financial_reports (
                CD_CVM INTEGER,
                COMPANY_NAME TEXT,
                REPORT_YEAR INTEGER
            )
            """
        )
        conn.executemany(
            "INSERT INTO financial_reports (CD_CVM, COMPANY_NAME, REPORT_YEAR) VALUES (?, ?, ?)",
            [
                (9512, "PETROBRAS", 2024),
                (4170, "VALE", 2023),
            ],
        )
        conn.commit()


def _create_db_with_statements(path: Path, rows: list[tuple[int, str, int, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
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
        conn.executemany(
            """
            INSERT INTO financial_reports (CD_CVM, COMPANY_NAME, REPORT_YEAR, STATEMENT_TYPE)
            VALUES (?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()


def test_safe_name_replaces_slashes():
    assert _safe_name("A/B C\\D") == "A_B_C_D"


def test_minmax_normalize_behaviour():
    values = [10.0, 20.0, 30.0]
    assert _minmax_normalize(10.0, values) == pytest.approx(0.0)
    assert _minmax_normalize(30.0, values) == pytest.approx(1.0)
    assert _minmax_normalize(None, values) == pytest.approx(0.0)


def test_build_ranked_selection_uses_gap_and_market_data(tmp_path):
    project_root = tmp_path
    db_path = project_root / "data" / "db" / "cvm_financials.db"
    _create_db(db_path)

    service = IntelligentSelectorService(project_root)

    # Evita rede/cache real, mantendo teste deterministico.
    def fake_snapshot(ticker, _cache, _budget):
        if ticker == "PETR4.SA":
            return {"mktcap": 600_000_000_000.0, "avg_volume": 80_000_000.0, "fetched_at": None}
        if ticker == "VALE3.SA":
            return {"mktcap": 300_000_000_000.0, "avg_volume": 40_000_000.0, "fetched_at": None}
        return {"mktcap": 0.0, "avg_volume": 0.0, "fetched_at": None}

    service._load_market_snapshot = fake_snapshot  # type: ignore[method-assign]
    service._find_last_file_update = lambda _name: None  # type: ignore[method-assign]
    service._save_market_cache = lambda _cache: None  # type: ignore[method-assign]

    rows = service.build_ranked_selection(start_year=2022, end_year=2025, target_count=2)
    assert len(rows) == 2
    # year_gap is the primary sort key: VALE (gap=2) before PETROBRAS (gap=1)
    assert rows[0]["year_gap"] >= rows[1]["year_gap"]
    assert {"PETROBRAS", "VALE"} == {r["company_name"] for r in rows}


def test_build_ranked_selection_deprioritizes_recently_updated_companies(tmp_path):
    project_root = tmp_path
    db_path = project_root / "data" / "db" / "cvm_financials.db"
    _create_db(db_path)

    # Ajusta ambas para mesmo ano para forcar desempate por recencia de update
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("UPDATE financial_reports SET REPORT_YEAR = 2025")
        conn.commit()

    service = IntelligentSelectorService(project_root)

    def fake_snapshot(ticker, _cache, _budget):
        if ticker == "PETR4.SA":
            return {"mktcap": 700_000_000_000.0, "avg_volume": 100_000_000.0, "fetched_at": None}
        if ticker == "VALE3.SA":
            return {"mktcap": 300_000_000_000.0, "avg_volume": 40_000_000.0, "fetched_at": None}
        return {"mktcap": 0.0, "avg_volume": 0.0, "fetched_at": None}

    recent = datetime.now() - timedelta(hours=1)
    older = datetime.now() - timedelta(days=10)
    service._load_market_snapshot = fake_snapshot  # type: ignore[method-assign]
    service._find_last_file_update = lambda name: recent if name == "PETROBRAS" else older  # type: ignore[method-assign]
    service._save_market_cache = lambda _cache: None  # type: ignore[method-assign]

    rows = service.build_ranked_selection(start_year=2024, end_year=2025, target_count=2)
    assert len(rows) == 2
    # PETROBRAS tem maior importancia, mas por estar atualizada recentemente
    # deve perder prioridade para o proximo lote.
    assert rows[0]["company_name"] == "VALE"
    assert rows[0]["recent_update"] == "Nao"
    assert rows[1]["company_name"] == "PETROBRAS"
    assert rows[1]["recent_update"] == "Sim"


def test_build_ranked_selection_uses_refresh_status_recency_as_primary_source(tmp_path):
    project_root = tmp_path
    db_path = project_root / "data" / "db" / "cvm_financials.db"
    _create_db(db_path)

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("UPDATE financial_reports SET REPORT_YEAR = 2025")
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
        recent = (datetime.now() - timedelta(hours=1)).replace(microsecond=0).isoformat()
        older = (datetime.now() - timedelta(days=10)).replace(microsecond=0).isoformat()
        conn.executemany(
            """
            INSERT INTO company_refresh_status (
                cd_cvm, company_name, source_scope, last_attempt_at, last_success_at,
                last_status, last_error, last_start_year, last_end_year, last_rows_inserted, updated_at
            ) VALUES (?, ?, 'local', ?, ?, 'success', NULL, 2024, 2025, 1, ?)
            """,
            [
                (9512, "PETROBRAS", recent, recent, recent),
                (4170, "VALE", older, older, older),
            ],
        )
        conn.commit()

    service = IntelligentSelectorService(project_root)

    def fake_snapshot(ticker, _cache, _budget):
        if ticker == "PETR4.SA":
            return {"mktcap": 700_000_000_000.0, "avg_volume": 100_000_000.0, "fetched_at": None}
        if ticker == "VALE3.SA":
            return {"mktcap": 300_000_000_000.0, "avg_volume": 40_000_000.0, "fetched_at": None}
        return {"mktcap": 0.0, "avg_volume": 0.0, "fetched_at": None}

    service._load_market_snapshot = fake_snapshot  # type: ignore[method-assign]
    service._find_last_file_update = lambda _name: None  # type: ignore[method-assign]
    service._save_market_cache = lambda _cache: None  # type: ignore[method-assign]

    rows = service.build_ranked_selection(start_year=2024, end_year=2025, target_count=2)
    assert rows[0]["company_name"] == "VALE"
    assert rows[1]["company_name"] == "PETROBRAS"


def test_build_ranked_selection_prioritizes_only_end_year_history(tmp_path):
    project_root = tmp_path
    db_path = project_root / "data" / "db" / "cvm_financials.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE financial_reports (
                CD_CVM INTEGER,
                COMPANY_NAME TEXT,
                REPORT_YEAR INTEGER
            )
            """
        )
        conn.executemany(
            "INSERT INTO financial_reports (CD_CVM, COMPANY_NAME, REPORT_YEAR) VALUES (?, ?, ?)",
            [
                (9512, "PETROBRAS", 2022),
                (9512, "PETROBRAS", 2023),
                (9512, "PETROBRAS", 2024),
                (9512, "PETROBRAS", 2025),
                (4170, "VALE", 2025),
            ],
        )
        conn.commit()

    service = IntelligentSelectorService(project_root)

    def fake_snapshot(ticker, _cache, _budget):
        if ticker == "PETR4.SA":
            return {"mktcap": 700_000_000_000.0, "avg_volume": 100_000_000.0, "fetched_at": None}
        if ticker == "VALE3.SA":
            return {"mktcap": 300_000_000_000.0, "avg_volume": 40_000_000.0, "fetched_at": None}
        return {"mktcap": 0.0, "avg_volume": 0.0, "fetched_at": None}

    service._load_market_snapshot = fake_snapshot  # type: ignore[method-assign]
    service._find_last_file_update = lambda _name: None  # type: ignore[method-assign]
    service._save_market_cache = lambda _cache: None  # type: ignore[method-assign]

    rows = service.build_ranked_selection(start_year=2022, end_year=2025, target_count=2)
    assert len(rows) == 2
    assert rows[0]["company_name"] == "VALE"
    assert rows[0]["only_end_year_history"] is True
    assert rows[0]["coverage"] == "So ano final"
    assert rows[1]["company_name"] == "PETROBRAS"
    assert rows[1]["only_end_year_history"] is False


def test_update_worker_sync_refresh_status_writes_success_rows(tmp_path):
    db_path = tmp_path / "cvm_financials.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE financial_reports (
                CD_CVM INTEGER,
                REPORT_YEAR INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE companies (
                cd_cvm INTEGER PRIMARY KEY,
                company_name TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            'INSERT INTO financial_reports (CD_CVM, REPORT_YEAR) VALUES (?, ?)',
            [(9512, 2024), (9512, 2025), (4170, 2025)],
        )
        conn.execute(
            """
            INSERT INTO companies (cd_cvm, company_name, updated_at)
            VALUES (9512, 'PETROBRAS OLD', '2020-01-01T00:00:00')
            """
        )
        conn.commit()

    worker = UpdateWorker(
        companies=["9512"],
        start_year=2024,
        end_year=2025,
        max_workers=2,
    )
    synced = worker._sync_refresh_status(
        db_path=db_path,
        results={
            "9512": {
                "company_name": "PETROBRAS",
                "cvm_code": 9512,
                "status": "success",
                "rows_inserted": 2,
                "error": None,
            }
        },
    )

    assert synced == 1
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            """
            SELECT cd_cvm, company_name, last_status, last_start_year, last_end_year, last_rows_inserted, last_success_at
            FROM company_refresh_status
            WHERE cd_cvm = 9512
            """
        ).fetchone()
        company_row = conn.execute(
            """
            SELECT company_name, updated_at
            FROM companies
            WHERE cd_cvm = 9512
            """
        ).fetchone()

    assert row is not None
    assert company_row is not None
    assert row[0] == 9512
    assert row[1] == "PETROBRAS"
    assert row[2] == "success"
    assert row[3] == 2024
    assert row[4] == 2025
    assert row[5] == 2
    assert company_row[0] == "PETROBRAS"
    assert company_row[1] == row[6]


def test_update_worker_sync_refresh_status_records_error_without_overwriting_last_success(tmp_path):
    db_path = tmp_path / "cvm_financials.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE financial_reports (
                CD_CVM INTEGER,
                REPORT_YEAR INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE company_refresh_status (
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
            INSERT INTO company_refresh_status
            (cd_cvm, company_name, source_scope, last_attempt_at, last_success_at, last_status, last_error,
             last_start_year, last_end_year, last_rows_inserted, updated_at)
            VALUES
            (9512, 'PETROBRAS', 'local', '2026-01-01T00:00:00', '2026-01-01T00:00:00', 'success', NULL, 2024, 2025, 2, '2026-01-01T00:00:00')
            """
        )
        conn.commit()

    worker = UpdateWorker(
        companies=["9512"],
        start_year=2024,
        end_year=2025,
        max_workers=2,
    )
    synced = worker._sync_refresh_status(
        db_path=db_path,
        results={
            "9512": {
                "company_name": "PETROBRAS",
                "cvm_code": 9512,
                "status": "error",
                "rows_inserted": 0,
                "error": "OperationalError: database is locked",
            }
        },
    )

    assert synced == 1
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            """
            SELECT last_status, last_error, last_success_at
            FROM company_refresh_status
            WHERE cd_cvm = 9512
            """
        ).fetchone()

    assert row is not None
    assert row[0] == "error"
    assert "database is locked" in row[1]
    assert row[2] == "2026-01-01T00:00:00"


def test_update_worker_build_company_year_plan_skips_completed_company_years(tmp_path):
    db_path = tmp_path / "cvm_financials.db"
    _create_db_with_statements(
        db_path,
        [
            (9512, "PETROBRAS", 2024, "BPA"),
            (9512, "PETROBRAS", 2024, "BPP"),
            (9512, "PETROBRAS", 2024, "DRE"),
            (9512, "PETROBRAS", 2024, "DFC"),
            (9512, "PETROBRAS", 2025, "BPA"),
            (9512, "PETROBRAS", 2025, "BPP"),
            (9512, "PETROBRAS", 2025, "DRE"),
            (4170, "VALE", 2024, "BPA"),
            (4170, "VALE", 2024, "BPP"),
            (4170, "VALE", 2024, "DRE"),
            (4170, "VALE", 2024, "DFC"),
            (4170, "VALE", 2025, "BPA"),
            (4170, "VALE", 2025, "BPP"),
            (4170, "VALE", 2025, "DRE"),
            (4170, "VALE", 2025, "DFC"),
        ],
    )

    worker = UpdateWorker(
        companies=["9512", "4170"],
        start_year=2024,
        end_year=2025,
        max_workers=2,
        skip_complete_company_years=True,
        enable_fast_lane=False,
        force_refresh=False,
    )
    planned_companies, year_overrides, stats = worker._build_company_year_plan(db_path)

    assert planned_companies == ["9512"]
    assert year_overrides[9512] == [2025]
    assert stats["requested_company_years"] == 4
    assert stats["planned_company_years"] == 1
    assert stats["skipped_complete_company_years"] == 3
    assert stats["skipped_companies_all_complete"] == 1


def test_update_worker_build_company_year_plan_fast_lane_recent_years(tmp_path):
    db_path = tmp_path / "cvm_financials.db"
    _create_db_with_statements(db_path, [])

    current_year = datetime.now().year
    worker = UpdateWorker(
        companies=["9512"],
        start_year=current_year - 3,
        end_year=current_year,
        max_workers=2,
        skip_complete_company_years=True,
        enable_fast_lane=True,
        force_refresh=False,
    )
    planned_companies, year_overrides, stats = worker._build_company_year_plan(db_path)

    # MAX_AUTO_REPORTING_YEAR_LAG=1 caps scope at current_year-1; current_year is excluded.
    # FAST_LANE_RECENT_YEARS=2 → recent_floor=current_year-1, so only [current_year-1] qualifies.
    assert planned_companies == ["9512"]
    assert year_overrides[9512] == [current_year - 1]
    assert stats["planned_company_years"] == 1
    assert stats["deferred_fast_lane_company_years"] == 2  # current_year-3 and current_year-2 deferred


def test_scan_processed_statement_presence_uses_incremental_index_cache(tmp_path):
    project_root = tmp_path
    processed_dir = project_root / "data" / "input" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    csv_path = processed_dir / "itr_cia_aberta_BPA_con_2025.csv"
    csv_path.write_text("CD_CVM;X\n9512;1\n4170;1\n", encoding="latin1")

    service = IntelligentSelectorService(project_root)
    presence_first = service._scan_processed_statement_presence(2025, 2025)
    assert (9512, 2025) in presence_first
    assert presence_first[(9512, 2025)] == {"BPA"}

    cache_path = project_root / "data" / "cache" / "processed_presence_index.json"
    assert cache_path.exists()
    cache_payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert "itr_cia_aberta_BPA_con_2025.csv" in cache_payload.get("files", {})

    with patch("desktop.services.pd.read_csv", side_effect=RuntimeError("should not read csv")):
        presence_second = service._scan_processed_statement_presence(2025, 2025)

    assert presence_second == presence_first


def test_build_base_health_snapshot_requires_full_package(tmp_path):
    project_root = tmp_path
    db_path = project_root / "data" / "db" / "cvm_financials.db"
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
        conn.executemany(
            """
            INSERT INTO financial_reports (CD_CVM, COMPANY_NAME, REPORT_YEAR, STATEMENT_TYPE)
            VALUES (?, ?, ?, ?)
            """,
            [
                (100, "ALFA", 2024, "BPA"),
                (100, "ALFA", 2024, "BPP"),
                (100, "ALFA", 2024, "DRE"),
                (100, "ALFA", 2024, "DFC"),
                (100, "ALFA", 2025, "BPA"),
                (100, "ALFA", 2025, "BPP"),
                (100, "ALFA", 2025, "DRE"),
                (200, "BETA", 2024, "BPA"),
                (200, "BETA", 2024, "BPP"),
                (200, "BETA", 2024, "DRE"),
                (200, "BETA", 2024, "DFC"),
                (200, "BETA", 2025, "BPA"),
                (200, "BETA", 2025, "BPP"),
                (200, "BETA", 2025, "DRE"),
                (200, "BETA", 2025, "DFC"),
            ],
        )
        conn.execute(
            """
            CREATE TABLE company_refresh_status (
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
            INSERT INTO company_refresh_status
            (cd_cvm, company_name, source_scope, last_attempt_at, last_success_at, last_status, last_error,
             last_start_year, last_end_year, last_rows_inserted, updated_at)
            VALUES (100, 'ALFA', 'local', '2026-03-30T10:00:00', '2026-03-30T10:00:00', 'success', NULL, 2024, 2025, 10, '2026-03-30T10:00:00')
            """
        )
        conn.commit()

    service = IntelligentSelectorService(project_root)
    service._load_active_universe = lambda: [  # type: ignore[method-assign]
        {"cd_cvm": 100, "company_name": "ALFA"},
        {"cd_cvm": 200, "company_name": "BETA"},
    ]
    service._scan_processed_statement_presence = lambda _s, _e: {}  # type: ignore[method-assign]

    snapshot = service.build_base_health_snapshot(2024, 2025, force_refresh=True)
    global_stats = snapshot["global"]
    assert global_stats["total_cells"] == 4
    assert global_stats["completed_cells"] == 3
    assert global_stats["missing_cells"] == 1

    year_2025 = [row for row in snapshot["per_year"] if row["year"] == 2025][0]
    assert year_2025["completed"] == 1
    assert year_2025["missing"] == 1

    assert snapshot["throughput"]["per_hour"] is None
    assert snapshot["top_lagging"][0]["company_name"] == "ALFA"
    assert snapshot["top_lagging"][0]["missing_years_count"] == 1
    assert snapshot["health_status"] in {"critico", "atencao", "ok"}
    assert 0.0 <= float(snapshot["health_score"]) <= 100.0
    assert "progress_delta" in snapshot
    assert "risks_summary" in snapshot
    assert "prioritized_companies" in snapshot
