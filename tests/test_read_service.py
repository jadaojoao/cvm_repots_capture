# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3

from src.read_service import CVMReadService
from src.settings import build_settings


def test_list_refresh_status_returns_stable_dto_contract(tmp_path):
    settings = build_settings(project_root=tmp_path)
    db_path = settings.paths.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(db_path)) as conn:
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
        conn.execute(
            """
            INSERT INTO company_refresh_status (
                cd_cvm, company_name, source_scope,
                last_attempt_at, last_success_at, last_status, last_error,
                last_start_year, last_end_year, last_rows_inserted, updated_at
            ) VALUES (
                9512, 'PETROBRAS', 'local',
                '2026-04-07T10:00:00', '2026-04-07T10:01:00', 'success', NULL,
                2024, 2025, 120, '2026-04-07T10:01:00'
            )
            """
        )
        conn.commit()

    service = CVMReadService(settings=settings)
    rows = service.list_refresh_status()

    assert len(rows) == 1
    dto = rows[0]
    assert dto.cd_cvm == 9512
    assert dto.company_name == "PETROBRAS"
    assert dto.last_status == "success"
    assert dto.last_rows_inserted == 120
    assert dto.to_dict()["source_scope"] == "local"
