# -*- coding: utf-8 -*-
"""
Regression tests for cross-dialect behavior in src/database.py.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database import CVMDatabase


class _RecorderConn:
    def __init__(self, fail_on_execute: bool = False):
        self.fail_on_execute = fail_on_execute
        self.calls: list[tuple[str, dict | None]] = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        if self.fail_on_execute:
            raise RuntimeError("forced execute failure")
        return None


class _Ctx:
    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, dialect_name: str):
        self.dialect = SimpleNamespace(name=dialect_name)
        self.connect_conn = _RecorderConn()
        self.begin_conn = _RecorderConn()
        self.connect_calls = 0
        self.begin_calls = 0

    def connect(self):
        self.connect_calls += 1
        return _Ctx(self.connect_conn)

    def begin(self):
        self.begin_calls += 1
        return _Ctx(self.begin_conn)


def _new_db_with_engine(engine):
    db = CVMDatabase.__new__(CVMDatabase)
    db._engine = engine
    return db


class _FakeFrame:
    def __init__(self, columns: list[str]):
        self.columns = columns
        self.calls: list[dict] = []

    def to_sql(self, *args, **kwargs):
        self.calls.append(kwargs)
        return None


def test_init_db_applies_pragmas_for_sqlite_only():
    db = _new_db_with_engine(_FakeEngine("sqlite"))
    db._init_db()

    pragma_sql = "\n".join(sql for sql, _ in db._engine.connect_conn.calls)
    assert "PRAGMA journal_mode = WAL" in pragma_sql
    assert "PRAGMA synchronous = OFF" in pragma_sql

    ddl_sql = "\n".join(sql for sql, _ in db._engine.begin_conn.calls)
    assert "CREATE TABLE IF NOT EXISTS financial_reports" in ddl_sql
    assert "CREATE TABLE IF NOT EXISTS qa_logs" in ddl_sql


def test_init_db_skips_pragmas_for_postgresql():
    db = _new_db_with_engine(_FakeEngine("postgresql"))
    db._init_db()

    assert db._engine.connect_calls == 0
    ddl_sql = "\n".join(sql for sql, _ in db._engine.begin_conn.calls)
    assert "PRAGMA" not in ddl_sql
    assert "CREATE TABLE IF NOT EXISTS financial_reports" in ddl_sql


def test_upsert_company_metadata_uses_dialect_safe_sql():
    db = _new_db_with_engine(_FakeEngine("postgresql"))
    conn = _RecorderConn()

    db._upsert_company_metadata(
        conn,
        company_name="ACME S.A.",
        cvm_code=12345,
        company_type="comercial",
        setor_cvm="Energia",
        ticker_b3="ACME3.SA",
    )

    sql_joined = "\n".join(sql.lower() for sql, _ in conn.calls)
    assert "insert or ignore" not in sql_joined
    assert "strftime" not in sql_joined
    assert "where not exists" in sql_joined

    assert len(conn.calls) == 2
    insert_params = conn.calls[0][1]
    assert insert_params is not None
    assert isinstance(insert_params["updated_at"], str)
    assert "T" in insert_params["updated_at"]


def test_upsert_company_metadata_raises_on_failure():
    db = _new_db_with_engine(_FakeEngine("sqlite"))
    conn = _RecorderConn(fail_on_execute=True)

    with pytest.raises(RuntimeError):
        db._upsert_company_metadata(
            conn,
            company_name="BROKEN S.A.",
            cvm_code=999,
            company_type="comercial",
            setor_cvm=None,
            ticker_b3=None,
        )


def test_to_sql_with_retry_scales_chunksize_for_sqlite_variable_limit():
    db = _new_db_with_engine(_FakeEngine("sqlite"))
    frame = _FakeFrame(
        [
            "COMPANY_NAME", "CD_CVM", "COMPANY_TYPE", "STATEMENT_TYPE",
            "REPORT_YEAR", "PERIOD_LABEL", "LINE_ID_BASE", "CD_CONTA",
            "DS_CONTA", "STANDARD_NAME", "QA_CONFLICT", "VL_CONTA",
        ]
    )

    db._to_sql_with_retry("financial_reports", frame, _RecorderConn())

    assert len(frame.calls) == 1
    assert frame.calls[0]["chunksize"] == 75


def test_to_sql_with_retry_keeps_default_chunksize_for_postgresql():
    db = _new_db_with_engine(_FakeEngine("postgresql"))
    frame = _FakeFrame(["a", "b", "c"])

    db._to_sql_with_retry("financial_reports", frame, _RecorderConn())

    assert len(frame.calls) == 1
    assert frame.calls[0]["chunksize"] == 2000
