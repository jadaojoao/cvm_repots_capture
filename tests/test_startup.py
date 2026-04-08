# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3

from src.settings import build_settings
from src.startup import collect_startup_report


def _init_required_tables(db_path) -> None:
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
        conn.execute(
            """
            CREATE TABLE companies (
                cd_cvm INTEGER PRIMARY KEY,
                company_name TEXT NOT NULL
            )
            """
        )
        conn.commit()


def test_collect_startup_report_accepts_ready_environment(tmp_path):
    settings = build_settings(project_root=tmp_path)
    settings.paths.canonical_accounts_path.parent.mkdir(parents=True, exist_ok=True)
    settings.paths.canonical_accounts_path.write_text("CD_CONTA,STANDARD_NAME\n1,ATIVO\n", encoding="utf-8")
    _init_required_tables(settings.paths.db_path)

    report = collect_startup_report(
        settings,
        require_database=True,
        required_tables=("financial_reports", "companies"),
        require_canonical_accounts=True,
        warn_on_legacy_data=False,
    )

    assert report.ok is True
    assert report.issues == ()


def test_collect_startup_report_flags_broken_venv_legacy_and_missing_canonical(tmp_path):
    settings = build_settings(project_root=tmp_path)
    broken_venv_dir = tmp_path / ".venv" / "Scripts"
    broken_venv_dir.mkdir(parents=True, exist_ok=True)

    settings.paths.input_dir.mkdir(parents=True, exist_ok=True)
    (settings.paths.input_dir / "dfp_cia_aberta_2025.zip").write_text("zip", encoding="utf-8")

    legacy_dir = settings.paths.legacy_data_paths[0]
    legacy_dir.mkdir(parents=True, exist_ok=True)
    (legacy_dir / "old.csv").write_text("legacy", encoding="utf-8")

    report = collect_startup_report(
        settings,
        require_database=False,
        require_canonical_accounts=True,
        warn_on_legacy_data=True,
    )

    codes = {issue.code for issue in report.issues}
    assert "venv-broken" in codes
    assert "canonical-accounts-missing" in codes
    assert "noncanonical-input-layout" in codes
    assert "legacy-data-root" in codes
